"""Semantic Safety v5 — semantic decomposition into non-composable fragments."""

from __future__ import annotations

from typing import Any


class SemanticDecomposer:
    """Decompose holistic semantics into decoupled fragments."""

    def decompose(self, output: dict[str, Any], *, max_depth: int = 3) -> list[dict[str, Any]]:
        fragments: list[dict[str, Any]] = []
        self._walk(output, fragments, depth=0, max_depth=max_depth)
        return fragments

    def _walk(
        self,
        node: Any,
        out: list[dict[str, Any]],
        *,
        depth: int,
        max_depth: int,
        prefix: str = "",
    ) -> None:
        if depth > max_depth:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                path = f"{prefix}.{key}" if prefix else key
                out.append(
                    {
                        "token": path,
                        "semantic_weight": "decoupled",
                        "context_dependency": "removed",
                        "value_type": type(value).__name__,
                    }
                )
                if isinstance(value, (dict, list)):
                    self._walk(value, out, depth=depth + 1, max_depth=max_depth, prefix=path)
        elif isinstance(node, list):
            for i, item in enumerate(node[:8]):
                self._walk(item, out, depth=depth + 1, max_depth=max_depth, prefix=f"{prefix}[{i}]")
