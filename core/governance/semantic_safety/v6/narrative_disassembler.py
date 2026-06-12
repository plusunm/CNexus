"""Semantic Safety v6 — narrative disassembler."""

from __future__ import annotations

from typing import Any


class NarrativeDisassembler:
    """Disassemble narrative strings into non-constructible token fields."""

    def disassemble(self, narrative: str) -> dict[str, Any]:
        words = narrative.split()
        return {
            "tokens": words,
            "structure": "non-narrative",
            "coherence_chain": "broken",
            "token_count": len(words),
        }

    def disassemble_tree(self, node: Any, *, prefix: str = "") -> dict[str, Any]:
        if isinstance(node, str) and len(node.split()) > 2:
            return self.disassemble(node)
        if isinstance(node, dict):
            parts = [f"{k}={v}" for k, v in list(node.items())[:6] if isinstance(v, (str, int, float))]
            return self.disassemble(" ".join(parts) if parts else prefix or "empty")
        return {"tokens": [str(node)], "structure": "non-narrative", "coherence_chain": "broken", "token_count": 1}
